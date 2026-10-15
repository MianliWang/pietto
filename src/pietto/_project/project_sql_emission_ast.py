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
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_sets as setting
from pietto._project import project_sql_emission_values as valuing
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project.project_sql_emission_contract import (
    Blocker,
    BoundField,
    BoundSource,
    PreparedEmission,
    CompiledPreparedEmission,
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
    value: parameters.SQLNull | parameters.SQLAnchor | parameters.SQLUnary | None
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
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    plan = request.plan
    if type(request) is CompiledPreparedEmission:
        records = plan.ir.completed.root.records
        fields = tuple(
            r.address
            for r in records.values()
            if r.address.kind == "field"
            and (
                field is None
                or (
                    r.get("ordinal") == field.ordinal
                    and any(
                        source.owner is owner
                        and any(f is field for f in source.fields)
                        and source.position == r.get("source").position
                        for source in request.sources
                    )
                )
            )
        )
        contexts = tuple(
            plan.references[r.address]
            for r in records.values()
            if r.address.kind == "expression_context"
            and any(a in fields for a in r.get("fields"))
        )
        return tuple(
            p
            for p in request.premises
            if p.scope == "statement"
            or p.scope is owner
            or (
                field is not None
                and type(p.scope) is tuple
                and p.scope[0] is owner
                and any(p.scope[1] is c for c in contexts)
            )
        )
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


def representation_problem(field: BoundField, family: str) -> tuple[str, str] | None:
    value = json.loads(field.representation)
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
        from pietto._project.project_scalar_meaning import _source_entry

        if (
            field.scalar_meaning is None
            or _source_entry(field.scalar_meaning, field.field) is None
        ):
            return "PIE-B1004", "logical_temporal_or_uuid_meaning_missing"
    nullability = {"non_null": False, "nullable": True, "unknown": "unknown"}[
        field.field.effective_nullability.value
    ]
    return resolved_representation_problem(
        logical.name,
        nullability,
        value,
        family,
        None
        if field.decimal is None
        else (field.decimal.precision, field.decimal.scale),
    )


def resolved_representation_problem(
    tag, nullability, value, family, decimal
) -> tuple[str, str] | None:
    """Existing target representation law after resolved logical admission."""
    storage, domain = value["storage"], value["domain"]
    if value["nullable"] != nullability or type(value["nullable"]) is not type(
        nullability
    ):
        return "PIE-B1002", "nullability_mismatch"
    kind = storage["kind"]
    prefix = "pg_" if family == "postgres" else "my_"
    valid = kind.startswith(prefix)
    if tag == "Int":
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
    elif tag == "Bool":
        valid = (
            valid and kind in {"pg_bool", "my_bool01"} and domain["kind"] == "bool01"
        )
    elif tag == "Text":
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
    elif tag == "Decimal":
        if decimal is None:
            return "PIE-B1004", "validated_decimal_parameters_missing"
        valid = (
            valid
            and kind in {"pg_numeric", "my_decimal"}
            and domain["kind"] == "decimal"
        )
        if valid:
            pair = decimal
            valid = (
                pair
                == (storage["precision"], storage["scale"])
                == (domain["precision"], domain["scale"])
                and 1 <= pair[0] <= 65
                and 0 <= pair[1] <= min(pair[0], 30)
            )
    elif tag == "Timestamp":
        valid = (
            valid
            and storage
            == {
                "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                "fractional_seconds": 6,
            }
            and domain == {"kind": "timestamp"}
        )
    elif tag == "UUID":
        valid = (
            valid
            and storage
            == {"kind": "pg_uuid" if family == "postgres" else "my_uuid_bytes"}
            and domain == {"kind": "uuid", "encoding": "standard_bytes"}
        )
    elif tag == "Float":
        valid = (
            valid
            and kind in {"pg_float8", "my_double"}
            and domain["kind"] == "finite_float"
        )
    else:
        return "PIE-B1003", "representation_not_in_initial_domain"
    return None if valid else ("PIE-B1002", "physical_storage_or_domain_mismatch")


def operator_premise_problems(premises, family, parameterized):
    result: list[tuple[str, str]] = []
    keys = {"operator_environment": "builtin_only"}
    if parameterized:
        keys["parameter_protocol"] = (
            "postgres_extended" if family == "postgres" else "mysql_prepared"
        )
    for key, expected in keys.items():
        found = [p for p in premises if p.scope == "statement" and p.key == key]
        if not found:
            result.append(("PIE-B1004", key + "_declaration_missing"))
        elif any(json.loads(p.value) != expected for p in found):
            result.append(("PIE-B1005", key + "_declaration_mismatch"))
    return tuple(result)


def naming_premise_problems(premises, family):
    result: list[tuple[str, str]] = []
    names = [p for p in premises if p.key == "identifier_case"]
    expected = "quoted_exact" if family == "postgres" else "lower_case_table_names=0"
    if not names:
        result.append(("PIE-B1004", "identifier_case_declaration_missing"))
    elif any(json.loads(p.value) != expected for p in names):
        result.append(("PIE-B1005", "identifier_case_declaration_mismatch"))
    return tuple(result)


def source_premise_problems(premises, family):
    result: list[tuple[str, str]] = []
    for key in ("row_domain_matches", "read_only_object"):
        values = [p for p in premises if p.key == key]
        if not values or any(p.value != b"true" for p in values):
            result.append(("PIE-B1001", key + "_declaration_required"))
    clients = [p for p in premises if p.key == "client_encoding"]
    if not clients:
        result.append(("PIE-B1004", "client_encoding_declaration_missing"))
    elif any(
        json.loads(p.value) != ("UTF8" if family == "postgres" else "utf8mb4")
        for p in clients
    ):
        result.append(("PIE-B1005", "client_encoding_mismatch"))
    return tuple(result)


def field_premise_problems(premises, representation):
    result: list[tuple[str, str]] = []
    domain = json.loads(representation)["domain"]
    for premise in premises:
        expected = domain if premise.key == "value_domain" else domain.get(premise.key)
        if expected is not None and json.loads(premise.value) != expected:
            result.append(("PIE-B1005", "field_domain_premise_mismatch"))
    return tuple(result)


def emission_blockers(request: PreparedEmission, *, _guarded=None):
    if _guarded is not None:
        from pietto._project.project_guard_preparation import verify_scope

        verify_scope(_guarded, request)
    plan = request.plan
    result = list(request.input_blockers)
    try:
        meaning = request.scalar_meaning
        if meaning is not None:
            from pietto._project.project_scalar_meaning import verify_scalar_meaning

            verify_scalar_meaning(meaning, request.verification)
        if any(
            f.scalar_meaning is not meaning
            for source in request.sources
            for f in source.fields
        ):
            raise ValueError("inconsistent retained meaning")
    except (ValueError, TypeError, AttributeError):
        return (Blocker("PIE-B1008", "scalar_meaning_correspondence"),)
    projection_only = projection_chain_shape(plan)
    if meaning is not None and meaning.entries and not projection_only:
        from pietto._project.project_scalar_meaning import operations_admitted

        if not operations_admitted(meaning):
            return (
                *result,
                Blocker("PIE-B1003", "scalar_meaning_requires_field_projection"),
            )

    def add(code, detail, subject=None, location=None):
        result.append(Blocker(code, detail, subject, location))

    if RELEASES.get(request.family) != request.release:
        add("PIE-B1003", "target_release_not_reviewed")
    admitted = projection_only
    realization = None
    if not admitted and (
        admitted_row_shape(plan) or joining.admitted_join_shape(plan, _guarded=_guarded)
    ):
        realization = realize_rows(request, _guarded=_guarded)
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
        if not setting.bodies_admitted(plan):
            for body in plan.set_bodies:
                add("PIE-B1003", "set_body_shape_not_admitted", body.ref)
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
    # The parameter protocol is needed exactly when a placeholder is rendered:
    # a bind-safe literal slot or a header-parameter read (a window argument
    # included), never an unread header.
    reads = sum(type(e) is row.ProjectSQLParameterRead for e in plan.expressions)
    reads += sum(a.parameter is not None for a in plan.window_arguments)
    if scalar_nodes or realization is not None:
        for problem in operator_premise_problems(
            request.premises, request.family, bool(plan.literal_slots) or reads > 0
        ):
            add(*problem, plan.scope)
    if len(plan.bind_uses) + reads > limits["parameters"]:
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
        for problem in naming_premise_problems(request.premises, request.family):
            add(*problem, plan.scope)
    for aspect in request.assessment.assessment.aspects:
        if any(
            state.value in {"exact_negative", "conflicting_facts"}
            for state in aspect.outcomes
        ):
            add("PIE-B1006", "negative_original_target_evidence", aspect.entry.subject)
    for obligation in request.report.report.summary.enforcement_required:
        add("PIE-B1006", "original_enforcement_not_fulfilled", obligation.entry.subject)
    if request.family == "mysql" and not plan.sources:
        # D70.05: a statement reading no physical relation (pure VALUES) needs a
        # non-vacuous source qualification; MySQL offers none in this phase.
        add(
            "PIE-B1003",
            "zero_physical_source_not_admitted_on_target",
            plan.scope,
            plan.values_bodies[0].relation.definition.body.span
            if plan.values_bodies
            else None,
        )
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
        for problem in source_premise_problems(used, request.family):
            add(*problem, source.ref)
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
            for problem in field_premise_problems(
                applicable_premises(request, bound.owner, field), field.representation
            ):
                add(*problem, subject)
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
    from pietto._project.project_sql_plan import CompiledSQLPlan

    if type(plan) is CompiledSQLPlan:
        from pietto._project.project_sql_plan_requirements import (
            compiled_requirement_rule,
        )

        return compiled_requirement_rule(plan, entry, generated_scopes=generated_scopes)
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
    rule = resulting.demand_rule(entry) or setting.demand_rule(entry)
    if rule is not None:
        return rule
    if entry.family.value == "fixed_literal_transport" or (
        entry.family.value == "expression"
        and type(plan.expressions[entry.subject.position])
        not in {
            row.ProjectSQLReference,
            row.ProjectSQLJoinedReference,
            row.ProjectSQLMatchReference,
            row.ProjectSQLCapturedField,
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
    row.ProjectSQLParameterRead,
    row.ProjectSQLReference,
    row.ProjectSQLUnary,
    row.ProjectSQLBinary,
    row.ProjectSQLComparison,
    row.ProjectSQLIsNull,
    row.ProjectSQLBetween,
    row.ProjectSQLConditional,
    row.ProjectSQLMembership,
    row.ProjectSQLCast,
    row.ProjectSQLScalarCall,
    row.ProjectSQLRelationExists,
    row.ProjectSQLRelationScalar,
    row.ProjectSQLRelationMembership,
    row.ProjectSQLCapturedField,
)
# Expression reads that may render a capturing let inline at their own site.
INLINE_READS = (
    row.ProjectSQLRelationExists,
    row.ProjectSQLRelationScalar,
    row.ProjectSQLRelationMembership,
)
# Targets whose expression reads may render a capturing let's ORDER BY and
# LIMIT inside the read (D70.05); MySQL takes them only LATERAL.
ORDERED_INLINE_READ_TARGETS = frozenset({"postgres"})
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


def inline_body(unit) -> bool:
    """A capturing let's stage body, rendered inside the read of the let; its
    ORDER BY and LIMIT, if it has them, are one more inline (result) body."""
    return (
        type(unit) in (RowBody, resulting.RowResultBody)
        and unit.symbol is None
        and not unit.final
    )


def inline_input(unit):
    """The inline body one inline body reads, or None."""
    scan = unit.scan
    if type(scan) in (RowStageUse, resulting.RowResultUse) and inline_body(scan.body):
        return scan.body
    return None


def inline_chain(unit) -> tuple[Any, ...]:
    """An inline let's bodies read by ``unit``, innermost first."""
    chain = [unit]
    while (inner := inline_input(chain[-1])) is not None:
        chain.append(inner)
    return tuple(reversed(chain))


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
        return tuple(
            item
            for item in self.units
            if type(item) in {RowBody, resulting.RowResultBody}
        )


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
    # A VALUES definition is a zero-input leaf like a source, but it is also a
    # named producer: it owns its outputs and reads no input use. One leaf per
    # input chain; a set body or an expression block use is the only way a
    # statement closure reaches more than one leaf here.
    leaves = len(plan.sources) + len(plan.values_bodies)
    return bool(
        leaves
        and (leaves == 1 or plan.set_bodies or plan.expression_block_uses)
        and named
        and len(plan.input_uses)
        == len(named)
        - len(plan.values_bodies)
        + sum(len(body.operands) - 1 for body in plan.set_bodies)
        and len(plan.projections)
        + len(plan.aggregate_projections)
        + len(plan.window_projections)
        + sum(len(body.columns) for body in plan.set_bodies)
        + sum(len(body.columns) for body in plan.values_bodies)
        == len(plan.all_exports)
        and not plan.joins
        and all(type(e) in ADMITTED_STAGE_EXPRESSIONS for e in plan.expressions)
        and grouping.blocks_admitted(plan, single_input_use=True)
        and windowing.blocks_admitted(plan)
        and resulting.boundaries_admitted(plan)
        and setting.bodies_admitted(plan)
        and valuing.bodies_admitted(plan)
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
    *,
    _guarded=None,
    inline=None,
):
    """One JOIN input relation and the exact pre-match column it publishes.

    ``inline`` is the realized body of a capturing let this input executes
    LATERAL; it is never a CTE, so it replaces the named producer.
    """
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
            producer = (
                by_definition.get(use.original.producer) if inline is None else inline
            )
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
    elif joining.guarded_path_input(_guarded, request.plan, original):
        (definition,) = tuple(
            d for d in request.plan.bindings.definitions if d.ref is original.producer
        )
        if original.producer in source_refs:
            source = source_refs[original.producer]
            matches = tuple(
                s for s in request.sources if s.owner is source.source.owner
            )
            if len(matches) != 1:
                return None, ("PIE-B1001", "source_mapping_missing", source.ref, None)
            producer, source_ref = matches[0], source.ref
            for position, export in enumerate(definition.exports):
                fields = tuple(f for f in producer.fields if f.field is export.field)
                if len(fields) != 1:
                    return None, (
                        "PIE-B1001",
                        "guarded_path_source_field",
                        original.ref,
                        None,
                    )
                realization = rows.field_realization(fields[0])
                if realization is None:
                    return None, (
                        "PIE-B1004",
                        "join_input_field_representation_missing",
                        original.ref,
                        None,
                    )
                reads.append(
                    rows.StageColumn(
                        position,
                        fields[0].column,
                        export.ref,
                        realization,
                        field=fields[0],
                        source_port=export.ref,
                        scope=alias,
                    )
                )
        else:
            producer = by_definition.get(original.producer)
            if producer is None:
                return None, (
                    "PIE-B1001",
                    "named_producer_not_realized",
                    original.ref,
                    None,
                )
            (layout,) = tuple(
                d for d in request.layout.definitions if d.original is definition
            )
            if len(layout.terminals) != len(producer.columns):
                return None, ("PIE-B1001", "guarded_path_terminal", original.ref, None)
            for position, (column, terminal) in enumerate(
                zip(producer.columns, layout.terminals, strict=True)
            ):
                if column.column.terminal is not terminal.ref:
                    return None, (
                        "PIE-B1001",
                        "guarded_path_terminal",
                        original.ref,
                        None,
                    )
                reads.append(
                    replace(
                        column.column,
                        position=position,
                        name="c" + str(position),
                        scope=alias,
                    )
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
    *,
    _guarded=None,
    lateral=None,
):
    """Realize one JOIN occurrence as its own closed generated SELECT.

    ``lateral`` realizes a right input that executes a capturing let over the
    realized left input (LATERAL); it returns (None, None) for any other input.
    """
    inputs = []
    for reference in join.inputs:
        inline = None
        if lateral is not None and inputs:
            inline, problem = lateral(reference, inputs[0])
            if problem is not None:
                return None, problem
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
            _guarded=_guarded,
            inline=inline,
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


def realize_rows(request, *, _guarded=None):
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
    result_groups = resulting.boundaries_by_definition(plan)
    set_groups = setting.bodies_by_definition(plan)
    values_groups = valuing.bodies_by_definition(plan)
    # A capturing let is realized inline at its outer body's single read
    # (a correlated reference cannot live in a CTE: native probe S10-E).
    inline = {capture.inner for capture in plan.captures}
    # D70.05: MySQL takes a capturing let's ORDER BY and LIMIT only LATERAL.
    # Every scalar or IN read of such a let is refused at its own read, in
    # source order, before anything is realized.
    if family not in ORDERED_INLINE_READ_TARGETS:
        for block_use in sorted(
            (
                u
                for u in plan.expression_block_uses
                if u.producer in inline and result_groups.get(u.producer)
            ),
            key=lambda u: (
                u.expression.span.path or "",
                u.expression.span.line,
                u.expression.span.column,
            ),
        ):
            add(
                "PIE-B1003",
                "mysql_correlated_order_or_limit_read_not_admitted",
                block_use.ref,
                block_use.expression.span,
            )
        if problems:
            return RowRealization(tuple(problems), None)
    blocks_by_definition = {
        definition.original.ref: (definition, blocks) for definition, blocks in groups
    }
    producers = {use.ref: use.producer for use in plan.expression_block_uses}

    def stage_roots(definition, blocks):
        """Each stage body's (column roots, predicate roots) in stage order."""
        stage = stages.get(definition.original.ref)
        result = []
        for block in blocks:
            kind = block.kind.value
            if kind == "let":
                result.append(([lets[block.ref].expression], []))
            elif kind in {"where", "satisfying", "qualify"}:
                result.append(([], [filters[block.ref].predicate]))
            elif kind == "aggregate":
                assert stage is not None
                result.append(
                    (
                        [
                            argument
                            for value in aggregate_values.get(stage.ref, ())
                            for argument in value.arguments
                        ],
                        [],
                    )
                )
            elif kind == "window":
                # Header-parameter window arguments, in column and call order.
                result.append(
                    (
                        [
                            argument
                            for window in window_blocks.get(block.ref, ())
                            for argument in window_argument.get(window.ref, ())
                            if argument.parameter is not None
                        ],
                        [],
                    )
                )
            else:
                result.append(
                    ([p.expression for p in projections.get(block.ref, ())], [])
                )
        return result

    def nested_roots(parts, last):
        # An inline body renders its columns, its nested predecessor, then
        # its own predicate.
        if last < 0:
            return []
        columns, predicates = parts[last]
        return [*columns, *nested_roots(parts, last - 1), *predicates]

    ordered = []
    for definition, blocks in groups:
        if definition.original.ref in inline:
            continue
        for join in join_groups.get(definition.original.ref, ()):
            # A LATERAL right input's inline let renders before the ON.
            lateral = tuple(c for c in plan.captures if c.read is join.inputs[1])
            if lateral:
                parts = stage_roots(*blocks_by_definition[lateral[0].inner])
                ordered.extend(nested_roots(parts, len(parts) - 1))
            if join.on is not None:
                ordered.append(join.on)
        for columns, predicates in stage_roots(definition, blocks):
            ordered.extend((*columns, *predicates))
    occurrences = []

    def collect(reference):
        if type(reference) is windowing.plan_argument_type():
            physical = parameters.PHYSICAL[family][reference.parameter.tag]
            occurrences.append((reference, physical))
            return
        try:
            chains = rows.rendered_constant_chains(plan, reference)
            rendered = rows.rendered_tree_nodes(plan, reference)
        except ValueError:
            add("PIE-B1008", "expression_tree_structure", reference)
            return
        # Parameter reads join the literal chains in the one rendering order;
        # an inline let's own native occurrences render at its read, after a
        # membership read's left value (an inner read's let closes first).
        order = {id(node): i for i, node in enumerate(rendered)}

        def inline_key(node):
            start = order[id(node)]
            value = getattr(node, "value", None)
            end = start + (
                0 if value is None else len(rows.rendered_tree_nodes(plan, value))
            )
            return (end, 1, -start)

        native = sorted(
            (
                *(((order[id(leaf)], 0, 0), chain, leaf) for chain, leaf in chains),
                *(
                    ((order[id(node)], 0, 0), None, node)
                    for node in rendered
                    if type(node) is row.ProjectSQLParameterRead
                ),
                *(
                    (inline_key(node), None, node)
                    for node in rendered
                    if isinstance(node, INLINE_READS)
                    and producers.get(node.use) in inline
                ),
            ),
            key=lambda item: item[0],
        )
        for _, chain, leaf in native:
            if isinstance(leaf, INLINE_READS):
                definition, blocks = blocks_by_definition[producers[leaf.use]]
                parts = stage_roots(definition, blocks)
                for inner in nested_roots(parts, len(parts) - 1):
                    collect(inner)
                continue
            if type(leaf) is row.ProjectSQLParameterRead:
                occurrences.append(
                    (leaf, parameters.PHYSICAL[family][leaf.parameter.tag])
                )
                continue
            problem = parameters.chain_problem(plan, chain, family)
            if problem is not None:
                add(*problem, chain, leaf.site.occurrence.span)
            elif type(leaf) is row.ProjectSQLBoundLiteral:
                tag = parameters.tag_of(leaf)
                assert tag is not None
                occurrences.append((leaf, parameters.PHYSICAL[family][tag]))

    for reference in ordered:
        collect(reference)
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
    by_definition: dict[Any, RowBody | valuing.ValuesBody] = {}
    by_join: dict[Any, joining.JoinBody] = {}
    nodes = 0

    def realize_stages(definition, blocks, joined, captures):
        """Realize one definition's stage bodies; a capturing let is inline.

        ``captures`` maps each capture record of an inline let to the outer
        row scope of its single read; its bodies are never CTEs and
        never join ``units``: they are reachable only through that read.
        """
        nonlocal nodes
        inline_bodies: list[Any] = []
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
                        return None
                    scan = RowScan(source, matches[0], use, alias, binding)
                else:
                    producer = by_definition.get(use.producer)
                    if producer is None:
                        add("PIE-B1001", "named_producer_not_realized", use.ref)
                        return None
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
                    return None
                incoming.append(read)
            columns: list[Any] = []
            available = {
                port: read for port, read in zip(block.inputs, incoming, strict=True)
            }
            # Row values may also read whole blocks through this definition's
            # own expression block uses; stage columns never include them. An
            # inline let's own captured fields read its outer row scopes.
            readable = dict(available)
            if captures is not None:
                readable.update(captures)
            for block_use in plan.expression_block_uses:
                if block_use.consumer is not definition.original.ref:
                    continue
                if block_use.producer in inline:
                    target = _inline_target(block_use, block, scan, available)
                    if target is False:
                        return None
                    if target is not None:
                        readable[block_use.ref] = target
                    continue
                target = _block_target(request, block_use, by_definition, source_refs)
                if target is None:
                    add(
                        "PIE-B1001",
                        "expression_block_producer_not_realized",
                        block_use.ref,
                    )
                    return None
                readable[block_use.ref] = target
            kind = block.kind.value
            # A definition with result boundaries ends in its result body, so
            # its visible projection is a closed stage whose terminals are the
            # PROJECTION-role result ports rather than the canonical terminals.
            result_boundaries = result_groups.get(definition.original.ref, ())
            selected = definition.original.entry.owner is plan.scope.selected_owner
            final = kind == "projection" and selected and not result_boundaries
            projection_terminals = (
                resulting.projection_terminals(plan, block.ref)
                if kind == "projection" and result_boundaries
                else definition.terminals
            )
            stage = stages.get(definition.original.ref)
            aggregate_stage = None
            window_stage = None
            block_exports: tuple[Any, ...] = ()
            if kind != "projection":
                resolved = [stage_ports.get(ref) for ref in block.exports]
                if any(port is None for port in resolved):
                    add("PIE-B1001", "stage_export_not_bound", block.ref)
                    return None
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
                    return None
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
                    projection_terminals[: len(definition.original.exports)],
                    available,
                    tuple(aggregate_projections.get(block.ref, ())),
                    final,
                    symbol=SQLSymbol,
                )
                if built is None:
                    assert problem is not None
                    add(*problem)
                    return None
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
                            return None
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
                        native=uses,
                    )
                    if built is None:
                        assert problem is not None
                        add(*problem)
                        return None
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
                            return None
                        claims[entry.export] = entry
                    for entry in window_projection.get(block.ref, ()):
                        if entry.export in claims:
                            add("PIE-B1001", "projection_export_conflict", entry.ref)
                            return None
                        claims[entry.export] = entry
                    items = tuple(claims.get(export.ref) for export in exports)
                    if any(item is None for item in items):
                        add("PIE-B1001", "stage_export_denominator", block.ref)
                        return None
                else:
                    items = (lets[block.ref],) if kind == "let" else ()
                    if len(items) != len(exports):
                        add("PIE-B1001", "stage_export_denominator", block.ref)
                        return None
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
                        return None
                    terminal = projection_terminals[position]
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
                        projection_terminals[position],
                        available,
                        position,
                        label,
                        symbol=SQLSymbol,
                    )
                    if built is None:
                        assert problem is not None
                        add(*problem)
                        return None
                    columns.append(built)
                    continue
                value, problem = rows.build_row_value(
                    request,
                    readable,
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
                    return None
                terminal = (
                    projection_terminals[position] if kind == "projection" else export
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
                return None
            predicate = None
            if kind in {"where", "satisfying", "qualify"}:
                item = filters[block.ref]
                value, problem = rows.build_row_value(
                    request,
                    readable,
                    item.predicate,
                    uses,
                    reference_type=grouping.ProjectSQLResultReference
                    if kind == "satisfying"
                    else reference_type,
                )
                if value is None:
                    assert problem is not None
                    add(*problem, item.ref, item.site.occurrence.span)
                    return None
                realization = rows.realization_of(value, family)
                if realization.tag != "Bool" or realization.domain.get("kind") != (
                    "bool01"
                ):
                    add("PIE-B1002", "predicate_root_not_bool", item.ref)
                    return None
                if (
                    tuple(
                        (effect.truth.value, effect.retain_row)
                        for effect in item.retention_effects
                    )
                    != RETENTION
                ):
                    add("PIE-B1005", "predicate_retention_effects_changed", item.ref)
                    return None
                predicate = RowPredicate(item, item.predicate, value)
                nodes += _value_node_count(value)
            if kind == "projection" and result_boundaries:
                # ORDER without DISTINCT reads pre-projection values through
                # hidden helper ports; each one is carried as its own column of
                # this closed stage and never reaches the visible tuple.
                for helper in projection_terminals[len(columns) :]:
                    read = available.get(helper.source)
                    if helper.canonical is not None or read is None:
                        add("PIE-B1001", "result_helper_port_not_bound", helper.ref)
                        return None
                    position = len(columns)
                    label = f"c{position}"
                    columns.append(
                        RowCarryColumn(
                            position,
                            helper,
                            helper.source,
                            read,
                            SQLSymbol(position + 1, helper.ref, label),
                            label,
                            replace(
                                read, position=position, name=label, terminal=helper.ref
                            ),
                        )
                    )
            terminals = projection_terminals if kind == "projection" else block_exports
            if len(terminals) != len(columns):
                add("PIE-B1001", "stage_terminal_denominator", block.ref)
                return None
            # An inline body is neither final nor a CTE: it has no unit name.
            named = not final and captures is None
            body = RowBody(
                definition,
                block,
                index,
                scan,
                tuple(columns),
                tuple(terminals),
                predicate,
                final,
                SQLSymbol(len(units), block.ref, f"p{len(units)}") if named else None,
                tuple(
                    SQLSymbol(i, terminal.ref, f"c{i}")
                    for i, terminal in enumerate(terminals)
                )
                if named
                else (),
                aggregate_stage,
                window_stage,
            )
            previous = body
            if captures is not None:
                # An inline body's own structure counts like any other body.
                nodes += 3 + 2 * len(body.columns)
                inline_bodies.append(body)
                if kind == "projection" and result_boundaries:
                    # The let's ORDER BY and LIMIT: one more inline body over
                    # its projection, inside the same derived relation. Which
                    # reads may take them is decided before semantics
                    # (relation_captures.admitted_capture_body).
                    result, problem = resulting.build_result_body(
                        request,
                        definition,
                        result_boundaries,
                        body,
                        index=len(blocks),
                        final=False,
                        symbol=SQLSymbol,
                        inline=True,
                    )
                    if result is None:
                        assert problem is not None
                        add(*problem)
                        return None
                    nodes += 3 + 2 * len(result.columns) + resulting.node_count(result)
                    inline_bodies.append(result)
                continue
            bodies.append(body)
            units.append(body)
            if kind == "projection" and result_boundaries:
                result, problem = resulting.build_result_body(
                    request,
                    definition,
                    result_boundaries,
                    body,
                    index=len(units),
                    final=selected,
                    symbol=SQLSymbol,
                )
                if result is None:
                    assert problem is not None
                    add(*problem)
                    return None
                nodes += resulting.node_count(result)
                bodies.append(result)
                units.append(result)
                by_definition[definition.original.ref] = result
            elif kind == "projection":
                by_definition[definition.original.ref] = body
        return inline_bodies

    def _inline_target(block_use, block, scan, available):
        """Realize a capturing let inside the block of its single read.

        Returns the read's target, None in any other block of the reader, and
        False when the let cannot be realized there.
        """
        local = tuple(
            capture
            for capture in plan.captures
            if capture.edge.checkpoint.read is block_use.edge
        )
        if not local:
            add("PIE-B1001", "inline_read_without_capture", block_use.ref)
            return False
        if local[0].block is not block.ref:
            return None
        scopes = {}
        for capture in local:
            reads = tuple(available.get(port) for port in capture.ports)
            if capture.block is not block.ref or any(read is None for read in reads):
                add("PIE-B1001", "capture_outside_read_scope", capture.ref)
                return False
            scopes[capture.ref] = rows.SQLCaptureScope(capture, scan.symbol, reads)
        definition, blocks = blocks_by_definition[block_use.producer]
        inner = realize_stages(definition, blocks, (), scopes)
        if not inner:
            if inner is not None:
                add("PIE-B1001", "inline_let_without_body", block_use.ref)
            return False
        return rows.SQLBlockTarget(
            block_use,
            inner[-1],
            None,
            SQLSymbol(0, block_use.ref, f"e{block_use.ref.position}"),
        )

    def _lateral_input(reference, left):
        """Realize a capturing let as the LATERAL right input of its JOIN.

        Its captured fields read the JOIN's left input columns under the left
        alias; (None, None) when the input executes no capturing let.
        """
        local = tuple(c for c in plan.captures if c.read is reference)
        if not local:
            return None, None
        scopes = {}
        for capture in local:
            reads = []
            for port in capture.ports:
                positions = tuple(i for i, p in enumerate(left.ports) if p is port)
                if capture.block is not left.original.join or len(positions) != 1:
                    return None, (
                        "PIE-B1001",
                        "capture_outside_read_scope",
                        capture.ref,
                        None,
                    )
                reads.append(left.columns[positions[0]])
            scopes[capture.ref] = rows.SQLCaptureScope(
                capture, left.symbol, tuple(reads)
            )
        definition, blocks = blocks_by_definition[local[0].inner]
        inner = realize_stages(definition, blocks, (), scopes)
        if not inner:
            # The JOIN's caller records the one problem this returns.
            blocker = (
                problems.pop()
                if inner is None
                else Blocker("PIE-B1001", "inline_let_without_body", reference, None)
            )
            return None, (
                blocker.code,
                blocker.detail,
                blocker.subject,
                blocker.location,
            )
        return inner[-1], None

    for definition, blocks in groups:
        if definition.original.ref in inline:
            continue
        values_body = values_groups.get(definition.original.ref)
        if values_body is not None:
            # A VALUES definition is one closed zero-input unit; it reads no use.
            unit, problem = valuing.build_values_unit(
                request,
                definition,
                values_body,
                index=len(units),
                final=definition.original.entry.owner is plan.scope.selected_owner,
                symbol=SQLSymbol,
            )
            if unit is None:
                assert problem is not None
                add(*problem)
                return RowRealization(tuple(problems), None)
            units.append(unit)
            by_definition[definition.original.ref] = unit
            nodes += valuing.node_count(unit)
            continue
        set_body = set_groups.get(definition.original.ref)
        if set_body is not None:
            # A SET definition is one closed unit over its operands' terminals.
            unit, problem = setting.build_set_unit(
                request,
                definition,
                set_body,
                uses_by_ref=uses_by_ref,
                source_refs=source_refs,
                by_definition=by_definition,
                index=len(units),
                final=definition.original.entry.owner is plan.scope.selected_owner,
                symbol=SQLSymbol,
            )
            if unit is None:
                assert problem is not None
                add(*problem)
                return RowRealization(tuple(problems), None)
            units.append(unit)
            by_definition[definition.original.ref] = unit
            nodes += setting.node_count(unit)
            continue
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
                _guarded=_guarded,
                lateral=_lateral_input,
            )
            if unit is None:
                assert problem is not None
                add(*problem[:2], *problem[2:])
                return RowRealization(tuple(problems), None)
            units.append(unit)
            by_join[join.ref] = unit
            nodes += _join_node_count(unit)
        if realize_stages(definition, blocks, joined, None) is None:
            return RowRealization(tuple(problems), None)
    if not units or not getattr(units[-1], "final", False):
        add("PIE-B1001", "selected_body_not_last", plan.scope)
        return RowRealization(tuple(problems), None)
    nodes += 3 * len(bodies) + 2 * sum(len(b.columns) for b in bodies)
    nodes += sum(2 + len(b.columns) for b in bodies if not b.final)
    if plan.joins or plan.set_bodies or plan.values_bodies:
        return JoinRealization((), SQLJoinQuery(request, tuple(units), nodes))
    return RowRealization((), SQLRowQuery(request, tuple(bodies), nodes))


def _block_target(request, block_use, by_definition, source_refs):
    """The realized producer one expression block use reads, with its alias."""
    symbol = SQLSymbol(0, block_use.ref, f"e{block_use.ref.position}")
    source = source_refs.get(block_use.producer)
    if source is not None:
        matches = tuple(s for s in request.sources if s.owner is source.source.owner)
        if len(matches) != 1:
            return None
        return rows.SQLBlockTarget(block_use, matches[0], source, symbol)
    producer = by_definition.get(block_use.producer)
    if producer is None:
        return None
    return rows.SQLBlockTarget(block_use, producer, None, symbol)


def _value_node_count(value):
    total = 0
    for node in rows.value_nodes(value):
        total += (
            1
            if type(node)
            in {
                rows.SQLStageReference,
                rows.SQLOperation,
                rows.SQLBlockRead,
                rows.SQLCapturedReference,
            }
            # A read renders one anchor around one native placeholder.
            else 2
            if type(node) is rows.SQLParameterRead
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
    # A captured outer field is computed per outer row, never a fixed value.
    if type(value) not in {
        rows.SQLOperation,
        rows.SQLParameterRead,
        rows.SQLBlockRead,
        rows.SQLCapturedReference,
    }:
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
    for node in rows.rendered_value_nodes(value):
        if type(node) is rows.SQLParameterRead:
            result.append(
                GeneratedRequirement(
                    "query_parameter",
                    node.original.ref,
                    rows.REQUIREMENT_RULES["query_parameter"],
                    node_premises(request, node.realization, (), "parameter"),
                )
            )
            continue
        if type(node) is rows.SQLBlockRead:
            result.extend(block_read_requirements(request, node))
            continue
        if type(node) in {
            rows.SQLStageReference,
            rows.SQLOperation,
            rows.SQLCapturedReference,
        }:
            kind = rows.requirement_kind(node)
            operands = (
                tuple(rows.realization_of(o, family) for o in node.operands)
                if type(node) is rows.SQLOperation
                else ()
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


def block_read_requirements(request, node):
    """A block read, and the qualified scan when it reads a source; a
    membership operand keeps its own requirements after these."""
    target = node.target
    kind = rows.requirement_kind(node)
    result = [
        GeneratedRequirement(
            kind,
            node.original.ref,
            rows.REQUIREMENT_RULES[kind],
            node_premises(
                request,
                node.realization,
                rows.block_read_operands(node, request.family),
                kind,
            ),
        )
    ]
    if target.source is not None:
        # Like a JOIN input, the read keeps the scan obligations of the
        # physical relation it reads.
        producer = target.producer
        result.append(
            GeneratedRequirement(
                "qualified_scan",
                target,
                "R01",
                applicable_premises(request, producer.owner),
            )
        )
        result.extend(
            GeneratedRequirement(
                "source_representation",
                field,
                "R02",
                applicable_premises(request, producer.owner, field),
            )
            for field in producer.fields
        )
    elif inline_body(target.producer):
        # A capturing let read inline keeps every obligation of its own bodies.
        result.extend(_inline_requirements(request, target.producer))
    return tuple(result)


def _naming(request):
    return tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "identifier_case"
    )


def _inline_requirements(request, body):
    """An inline let's bodies, innermost first, each as its own derived table."""
    result = []
    inner = inline_input(body)
    if inner is not None:
        result.extend(_inline_requirements(request, inner))
    naming = _naming(request)
    if type(body) is resulting.RowResultBody:
        # The let's ORDER BY and LIMIT over its inline projection.
        result.append(
            GeneratedRequirement(
                "inline_stage_use", body.scan.body.block.ref, "R11", naming
            )
        )
        result.extend(
            resulting.requirements(request, body, naming, GeneratedRequirement)
        )
        result.append(GeneratedRequirement("read_only_select_bytes", body, "R23", ()))
        return result
    result.extend(_row_body_requirements(request, body, naming))
    return result


def scan_requirements(request, producer):
    """A physical relation read keeps its source realization and field
    representation obligations wherever it is scanned."""
    return (
        GeneratedRequirement(
            "qualified_scan",
            producer,
            "R01",
            applicable_premises(request, producer.owner),
        ),
        *(
            GeneratedRequirement(
                "source_representation",
                field,
                "R02",
                applicable_premises(request, producer.owner, field),
            )
            for field in producer.fields
        ),
    )


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
        elif inline_body(item.producer):
            # A capturing let executed LATERAL keeps its own bodies' obligations.
            result.append(
                GeneratedRequirement("lateral_input", item.original.ref, "R11", naming)
            )
            result.extend(_inline_requirements(request, item.producer))
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
        if type(unit.inputs[1].producer) in {
            resulting.RowResultBody,
            setting.SetBody,
            valuing.ValuesBody,
        }:
            # The right side is a complete post-DISTINCT/ORDER/LIMIT or SET
            # terminal; membership wraps that terminal, never its projection,
            # an operand or a source.
            result.append(
                GeneratedRequirement(
                    "complete_right_terminal",
                    unit.inputs[1].original.ref,
                    "R11",
                    naming,
                )
            )
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
    return original, row_generated_requirements(request, query)


def row_generated_requirements(request, query):
    """Original generated obligations over the actual closed dialect units."""
    units = getattr(query, "units", query.bodies)
    generated_scopes = len(units) > 1
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
        if type(unit) is setting.SetBody:
            generated.extend(
                setting.requirements(request, unit, naming, GeneratedRequirement)
            )
            generated.append(
                GeneratedRequirement("read_only_select_bytes", unit, "R23", ())
            )
            continue
        if type(unit) is valuing.ValuesBody:
            generated.extend(
                valuing.requirements(request, unit, naming, GeneratedRequirement)
            )
            generated.append(
                GeneratedRequirement("read_only_select_bytes", unit, "R23", ())
            )
            continue
        if type(unit) is resulting.RowResultBody:
            generated.append(
                GeneratedRequirement(
                    "stage_use", unit.scan.body.block.ref, "R03", naming
                )
            )
            generated.extend(
                GeneratedRequirement("stage_terminal", symbol.binding, "R03", naming)
                for symbol in unit.scan.body.cte_columns
            )
            generated.extend(
                resulting.requirements(request, unit, naming, GeneratedRequirement)
            )
            generated.append(
                GeneratedRequirement("read_only_select_bytes", unit, "R23", ())
            )
            continue
        generated.extend(_row_body_requirements(request, unit, naming))
    if generated_scopes:
        generated.append(
            GeneratedRequirement("nonrecursive_with_bytes", query, "R23", ())
        )
    return tuple(generated)


def _row_body_requirements(request, body, naming):
    """Every requirement one stage body's own structure and values introduce."""
    result = []
    scan = body.scan
    if type(scan) is RowScan:
        result.append(
            GeneratedRequirement(
                "qualified_scan",
                scan,
                "R01",
                applicable_premises(request, scan.realization.owner),
            )
        )
        result.extend(
            GeneratedRequirement(
                "source_representation",
                field,
                "R02",
                applicable_premises(request, scan.realization.owner, field),
            )
            for field in scan.realization.fields
        )
    elif type(scan) is RowNamedUse:
        result.append(GeneratedRequirement("named_use", scan.use.ref, "R03", naming))
        result.extend(
            GeneratedRequirement("immediate_terminal", link.terminal.ref, "R03", naming)
            for link in scan.binding.bindings
        )
    elif type(scan) is RowJoinUse:
        result.append(GeneratedRequirement("join_use", scan.tail.ref, "R07", naming))
        result.extend(
            GeneratedRequirement("join_terminal", symbol.binding, "R07", naming)
            for symbol in scan.body.cte_columns
        )
    elif inline_body(scan.body):
        result.append(
            GeneratedRequirement("inline_stage_use", scan.block.ref, "R11", naming)
        )
    else:
        result.append(GeneratedRequirement("stage_use", scan.block.ref, "R03", naming))
        result.extend(
            GeneratedRequirement("stage_terminal", symbol.binding, "R03", naming)
            for symbol in scan.body.cte_columns
        )
    operators = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "operator_environment"
    )
    if body.aggregation is not None:
        result.append(
            GeneratedRequirement(
                "aggregation", body.aggregation.aggregation.ref, "R12", operators
            )
        )
    for column in body.columns:
        if type(column) is RowCarryColumn:
            result.append(
                GeneratedRequirement("carry_projection", column.export.ref, "R05", ())
            )
            continue
        if type(column) is grouping.AggregateKeyColumn:
            result.append(
                GeneratedRequirement("group_key", column.key.ref, "R12", operators)
            )
            continue
        if type(column) is grouping.AggregateValueColumn:
            result.append(
                GeneratedRequirement(
                    "aggregate", column.aggregate.ref, "R13", operators
                )
            )
            if column.argument is not None:
                result.extend(value_requirements(request, column.argument))
            continue
        if type(column) is grouping.AggregateProjectionColumn:
            result.append(
                GeneratedRequirement(
                    "result_projection", column.projection.ref, "R12", ()
                )
            )
            continue
        if type(column) is windowing.WindowColumn:
            # R14 owns the computation, its input BAG and its result
            # representation; R15 owns the realized frame and named
            # components. Each generated structure keeps its own cause.
            result.append(
                GeneratedRequirement(
                    "window_computation", column.window.ref, "R14", operators
                )
            )
            result.append(
                GeneratedRequirement(
                    "window_specification", column.window.policy, "R15", ()
                )
            )
            result.extend(
                GeneratedRequirement(
                    "query_parameter",
                    argument.parameter.original.ref,
                    rows.REQUIREMENT_RULES["query_parameter"],
                    node_premises(
                        request, argument.parameter.realization, (), "parameter"
                    ),
                )
                for argument in column.arguments
                if argument.parameter is not None
            )
            # R15-INT-OFFSET-V1: a finite offset keeps its signed64 domain
            # obligation, and a RANGE offset its threshold arithmetic, per use.
            frame = column.specification.frame
            if frame is not None and any(
                kind in windowing.OFFSET_BOUNDS for kind, _ in (frame.start, frame.end)
            ):
                result.append(
                    GeneratedRequirement(
                        "window_frame_offset_domain",
                        column.window.policy,
                        "R15",
                        (),
                    )
                )
                if frame.unit == "range":
                    result.append(
                        GeneratedRequirement(
                            "window_range_arithmetic",
                            column.window.policy,
                            "R15",
                            operators,
                        )
                    )
            for _binding, read in column.specification.partitions:
                result.append(
                    GeneratedRequirement(
                        "window_partition_comparison", read.terminal, "R14", ()
                    )
                )
            for item in column.specification.orders:
                result.append(
                    GeneratedRequirement(
                        "window_order_comparison", item.read.terminal, "R14", ()
                    )
                )
            continue
        if type(column) is windowing.WindowProjectionColumn:
            result.append(
                GeneratedRequirement(
                    "window_result_projection", column.projection.ref, "R17", ()
                )
            )
            continue
        result.append(
            GeneratedRequirement("computed_projection", column.export.ref, "R05", ())
        )
        result.extend(value_requirements(request, column.value))
    if body.predicate is not None:
        satisfying = body.block.kind.value == "satisfying"
        result.append(
            GeneratedRequirement(
                "satisfying_root" if satisfying else "predicate_root",
                body.predicate.original.ref,
                "R12" if satisfying else "R06",
                operators,
            )
        )
        result.extend(value_requirements(request, body.predicate.value))
    result.append(GeneratedRequirement("read_only_select_bytes", body, "R23", ()))
    return result


def inline_values(body):
    """An inline let body's value roots in rendering order: its own columns,
    its inline predecessor, then its own predicate."""
    values = [column.value for column in body.columns if type(column) is RowValueColumn]
    inner = inline_input(body)
    if inner is not None:
        values.extend(inline_values(inner))
    if body.predicate is not None:
        values.append(body.predicate.value)
    return tuple(values)


def join_values(unit):
    """A JOIN unit's value roots in rendering order: a LATERAL right input's
    inline let, then the JOIN predicate."""
    values = []
    right = unit.inputs[1].producer
    if inline_body(right):
        values.extend(inline_values(right))
    if unit.predicate is not None:
        values.append(unit.predicate)
    return tuple(values)


def spliced_value_nodes(values):
    """Every value node in exact SQL order; an inline let's own nodes follow
    the read that renders it, after a membership read's left operand."""
    result = []
    for value in values:
        nodes = rows.rendered_value_nodes(value)
        pending: dict[int, list[tuple[Any, ...]]] = {}
        for position, node in enumerate(nodes):
            result.append(node)
            if type(node) is rows.SQLBlockRead and inline_body(node.target.producer):
                end = position + len(rows.rendered_value_nodes(node)) - 1
                pending.setdefault(end, []).append(
                    spliced_value_nodes(inline_values(node.target.producer))
                )
            # An inner read closes before the read whose operand holds it.
            for spliced in reversed(pending.pop(position, ())):
                result.extend(spliced)
    return tuple(result)


def row_parameter_leaves(query):
    """Native parameter leaves in exact rendering order across every unit."""
    result = []
    for body in getattr(query, "units", query.bodies):
        if type(body) is joining.JoinBody:
            values = list(join_values(body))
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
                elif type(column) is windowing.WindowColumn:
                    values.extend(column.arguments)
            if body.predicate is not None:
                values.append(body.predicate.value)
        for value in values:
            if type(value) is windowing.WindowArgument:
                if value.parameter is not None:
                    result.append(value.parameter)
                continue
            for node in spliced_value_nodes((value,)):
                if type(node) is rows.SQLParameterRead:
                    result.append(node)
                    continue
                if type(node) in {
                    rows.SQLStageReference,
                    rows.SQLOperation,
                    rows.SQLBlockRead,
                    rows.SQLCapturedReference,
                }:
                    continue
                result.extend(
                    leaf
                    for leaf in parameters.value_nodes(node)
                    if type(leaf) is parameters.SQLParameter
                )
    return tuple(result)


def row_binding_obligations(query):
    """Nodes whose check waits for a binding, in exact rendering order: row
    operations and header-parameter structural window counts."""
    result = []
    for value in row_value_roots(query):
        if type(value) is windowing.WindowArgument:
            nodes = () if value.parameter is None else (value.parameter,)
        else:
            nodes = tuple(
                node
                for node in spliced_value_nodes((value,))
                if type(node) is rows.SQLOperation
            )
        result.extend(node for node in nodes if node.realization.obligation is not None)
    return tuple(result)


def row_value_roots(query):
    """Rendered value roots in unit and SELECT-list order.

    This is deliberately a private view of the already verified AST.  It does
    not synthesize a second carrier: consumers which need a target-specific
    premise must derive it from these exact rendered roots.
    """
    result = []
    for body in getattr(query, "units", query.bodies):
        if type(body) is joining.JoinBody:
            result.extend(join_values(body))
            continue
        if type(body) is not RowBody:
            continue
        for column in body.columns:
            if type(column) is RowValueColumn:
                result.append(column.value)
            elif (
                type(column) is grouping.AggregateValueColumn
                and column.argument is not None
            ):
                result.append(column.argument)
            elif type(column) is windowing.WindowColumn:
                result.extend(column.arguments)
        if body.predicate is not None:
            result.append(body.predicate.value)
    return tuple(result)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSQLQuery:
    """Explicit compiled request over the same closed typed dialect units."""

    request: CompiledPreparedEmission
    units: tuple[Any, ...]
    nodes: int

    @property
    def bodies(self):
        return self.units
